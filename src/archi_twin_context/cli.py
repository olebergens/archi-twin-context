"""Command line interface for archi-twin-context"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .enricher import enrich_alert
from .loaders import load_alert, load_architecture_model, load_mapping
from .report import write_markdown_report

app = typer.Typer(help="Enrich Digital Twin alerts with Enterprise Architecture context.")


@app.callback()
def main() -> None:
    """Enrich Digital Twin alerts with Enterprise Architecture context"""


@app.command()
def enrich(
    alert: Path = typer.Option(..., "--alert", help="Path to the alert JSON file"),
    mapping: Path = typer.Option(..., "--mapping", help="Path to the asset mapping YAML file"),
    model: Path = typer.Option(..., "--model", help="Path to the architecture model YAML file"),
    report: Path | None = typer.Option(None, "--report", help="Optional Markdown report output path"),
    json_output: bool = typer.Option(False, "--json", help="Print the enriched alert as JSON to stdout"),
) -> None:
    """Read, enrich and report a Digital Twin alert"""

    console = Console(stderr=json_output)
    try:
        loaded_alert = load_alert(alert)
        mappings = load_mapping(mapping)
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


if __name__ == "__main__":
    app()
