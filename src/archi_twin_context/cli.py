"""Command line interface for archi-twin-context"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .adapters.postgres import resolve_database_url
from .enricher import enrich_alert
from .engine import run_engine
from .loaders import load_alert, load_archimate_xml_model, load_architecture_model, load_mapping
from .report import write_markdown_report

app = typer.Typer(help="Enrich Digital Twin alerts with Enterprise Architecture context.")


@app.callback()
def main() -> None:
    """Enrich Digital Twin alerts with Enterprise Architecture context"""


@app.command()
def enrich(
    alert: Path = typer.Option(..., "--alert", help="Path to the alert JSON file"),
    mapping: Path = typer.Option(..., "--mapping", help="Path to the asset mapping YAML file"),
    model: Path = typer.Option(..., "--model", help="Path to the architecture model file"),
    model_format: str = typer.Option(
        "auto",
        "--model-format",
        help="Architecture model format: auto, yaml or archimate-xml",
    ),
    xsd: Path | None = typer.Option(None, "--xsd", help="XSD path for ArchiMate XML validation"),
    report: Path | None = typer.Option(None, "--report", help="Optional Markdown report output path"),
    json_output: bool = typer.Option(False, "--json", help="Print the enriched alert as JSON to stdout"),
) -> None:
    """Read, enrich and report a Digital Twin alert"""

    console = Console(stderr=json_output)
    try:
        loaded_alert = load_alert(alert)
        mappings = load_mapping(mapping)
        resolved_format = _resolve_model_format(model, model_format)
        if resolved_format == "archimate-xml":
            if xsd is None:
                raise ValueError("ArchiMate XML import requires --xsd for schema validation")
            architecture_model = load_archimate_xml_model(model, xsd)
        else:
            architecture_model = load_architecture_model(model)

        enriched_alert = enrich_alert(loaded_alert, mappings, architecture_model)

        report_path: Path | None = None
        if report is not None:
            report_path = write_markdown_report(enriched_alert, report)

        console.print("[bold green]Alert enriched successfully.[/bold green]")
        console.print()
        console.print(f"[bold]Alert:[/bold] {enriched_alert.alert.alert_type}")
        console.print(f"[bold]Asset:[/bold] {enriched_alert.alert.asset_id}")
        console.print(f"[bold]Mapped EA Element:[/bold] {enriched_alert.mapped_element.name}")
        console.print(f"[bold]Risk Level:[/bold] {enriched_alert.risk_level}")
        console.print(f"[bold]Recommended Owner:[/bold] {enriched_alert.recommended_owner}")
        console.print(
            f"[bold]Recommended BPMN Process:[/bold] "
            f"{enriched_alert.recommended_bpmn_process or 'None'}"
        )
        if report_path is not None:
            console.print(f"[bold]Report written to[/bold] {report_path}")

        if json_output:
            typer.echo(enriched_alert.model_dump_json(indent=2))
    except Exception as exc:
        Console(stderr=True).print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def engine(
    mapping: Path = typer.Option(..., "--mapping", help="Path to the asset mapping YAML file"),
    model: Path = typer.Option(..., "--model", help="Path to the architecture model file"),
    database_url: str | None = typer.Option(None, "--database-url", help="PostgreSQL connection URL"),
    model_format: str = typer.Option(
        "auto",
        "--model-format",
        help="Architecture model format: auto, yaml or archimate-xml",
    ),
    xsd: Path | None = typer.Option(None, "--xsd", help="XSD path for ArchiMate XML validation"),
    poll_interval: float = typer.Option(2.0, "--poll-interval", min=0.1, help="Seconds to wait when no alerts are available"),
    batch_size: int = typer.Option(10, "--batch-size", min=1, help="Maximum alerts to claim per batch"),
    idle_log_every: int = typer.Option(10, "--idle-log-every", min=0, help="Log an idle heartbeat after this many empty polls; 0 disables it"),
) -> None:
    """Run the PostgreSQL-backed enrichment engine"""

    console = Console()
    try:
        console.print("[bold green]Starting enrichment engine.[/bold green]")
        console.print(f"Database: {resolve_database_url(database_url)}")
        run_engine(database_url, mapping, model, model_format, xsd, poll_interval, batch_size, idle_log_every)
    except KeyboardInterrupt:
        console.print("[yellow]Enrichment engine stopped.[/yellow]")
    except Exception as exc:
        Console(stderr=True).print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


def _resolve_model_format(model_path: Path, requested_format: str) -> str:
    normalized_format = requested_format.strip().lower()
    if normalized_format not in {"auto", "yaml", "archimate-xml"}:
        raise ValueError("--model-format must be one of: auto, yaml, archimate-xml")

    if normalized_format != "auto":
        return normalized_format

    if model_path.suffix.lower() == ".xml":
        return "archimate-xml"
    return "yaml"


if __name__ == "__main__":
    app()
