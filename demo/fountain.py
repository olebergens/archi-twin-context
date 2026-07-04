from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

import typer

from archi_twin_context.adapters.postgres import open_connection, persist_demo_alert, resolve_database_url
from archi_twin_context.models import DigitalTwinAlert


@dataclass(frozen=True)
class ProductionScenario:
    asset_id: str
    alert_type: str
    severity: str
    value_min: float | None
    value_max: float | None
    unit: str | None
    message_template: str
    status: str
    weight: int = 1


SCENARIOS = [
    ProductionScenario(
        asset_id="cnc-01",
        alert_type="vibration_high",
        severity="critical",
        value_min=6.5,
        value_max=9.5,
        unit="mm/s",
        message_template="Vibration threshold exceeded on CNC Milling Machine 01.",
        status="fault",
        weight=4,
    ),
    ProductionScenario(
        asset_id="cnc-01",
        alert_type="temperature_high",
        severity="warning",
        value_min=70.0,
        value_max=86.0,
        unit="celsius",
        message_template="Temperature increased on CNC Milling Machine 01.",
        status="warning",
        weight=3,
    ),
    ProductionScenario(
        asset_id="assembly-robot-02",
        alert_type="temperature_high",
        severity="critical",
        value_min=82.0,
        value_max=96.0,
        unit="celsius",
        message_template="Temperature threshold exceeded on Assembly Robot 02.",
        status="fault",
        weight=3,
    ),
    ProductionScenario(
        asset_id="assembly-robot-02",
        alert_type="availability_low",
        severity="warning",
        value_min=40.0,
        value_max=75.0,
        unit="percent",
        message_template="Availability dropped on Assembly Robot 02.",
        status="warning",
        weight=2,
    ),
    ProductionScenario(
        asset_id="packaging-line-03",
        alert_type="idle_detected",
        severity="info",
        value_min=8.0,
        value_max=25.0,
        unit="minutes",
        message_template="Packaging Line 03 has been idle longer than expected.",
        status="idle",
        weight=2,
    ),
    ProductionScenario(
        asset_id="packaging-line-03",
        alert_type="maintenance_required",
        severity="warning",
        value_min=None,
        value_max=None,
        unit=None,
        message_template="Preventive maintenance is required for Packaging Line 03.",
        status="maintenance",
        weight=1,
    ),
]

DEPENDENT_SCENARIOS = {
    "assembly-robot-02": ProductionScenario(
        asset_id="packaging-line-03",
        alert_type="idle_detected",
        severity="warning",
        value_min=10.0,
        value_max=35.0,
        unit="minutes",
        message_template="Packaging Line 03 is idle because upstream assembly output is interrupted.",
        status="idle",
        weight=1,
    )
}


class ProductionFountain:
    """Generate plausible abnormal production events for the demo twin"""

    def __init__(
        self,
        event_probability: float = 0.35,
        seed: int | None = None,
        scenarios: list[ProductionScenario] | None = None,
    ) -> None:
        if not 0 <= event_probability <= 1:
            raise ValueError("event_probability must be between 0 and 1")

        self.event_probability = event_probability
        self.random = random.Random(seed)
        self.scenarios = scenarios or SCENARIOS
        self.pending_scenarios: list[ProductionScenario] = []

    def next_alert(self) -> DigitalTwinAlert | None:
        if self.pending_scenarios:
            return self._alert_from_scenario(self.pending_scenarios.pop(0))

        if self.random.random() > self.event_probability:
            return None

        scenario = self._choose_scenario()
        if scenario.asset_id in DEPENDENT_SCENARIOS and scenario.status == "fault":
            self.pending_scenarios.append(DEPENDENT_SCENARIOS[scenario.asset_id])
        return self._alert_from_scenario(scenario)

    def _choose_scenario(self) -> ProductionScenario:
        return self.random.choices(
            self.scenarios,
            weights=[scenario.weight for scenario in self.scenarios],
            k=1,
        )[0]

    def _alert_from_scenario(self, scenario: ProductionScenario) -> DigitalTwinAlert:
        value: float | None = None
        if scenario.value_min is not None and scenario.value_max is not None:
            value = round(self.random.uniform(scenario.value_min, scenario.value_max), 2)

        return DigitalTwinAlert(
            alert_id=f"sim-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}",
            asset_id=scenario.asset_id,
            alert_type=scenario.alert_type,
            severity=scenario.severity,
            value=value,
            unit=scenario.unit,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            message=scenario.message_template,
        )


def status_for_alert(alert: DigitalTwinAlert) -> str:
    for scenario in SCENARIOS + list(DEPENDENT_SCENARIOS.values()):
        if scenario.asset_id == alert.asset_id and scenario.alert_type == alert.alert_type:
            return scenario.status
    if alert.severity == "critical":
        return "fault"
    return "warning" if alert.severity == "warning" else "idle"


def run_fountain(
    database_url: str | None,
    interval_seconds: float,
    event_probability: float,
    seed: int | None = None,
    idle_log_every: int = 10,
) -> None:
    fountain = ProductionFountain(event_probability=event_probability, seed=seed)
    idle_ticks = 0
    with open_connection(database_url) as conn:
        while True:
            alert = fountain.next_alert()
            if alert is not None:
                status = status_for_alert(alert)
                persist_demo_alert(conn, alert, status)
                conn.commit()
                idle_ticks = 0
                print(
                    "Generated alert "
                    f"{alert.alert_id}: {alert.asset_id} {alert.alert_type} "
                    f"severity={alert.severity} status={status} value={alert.value} {alert.unit or ''}".strip(),
                    flush=True,
                )
            else:
                idle_ticks += 1
                if idle_log_every > 0 and idle_ticks % idle_log_every == 0:
                    print("No abnormal event generated; production remains running.", flush=True)
            time.sleep(interval_seconds)


def main(
    database_url: str | None = typer.Option(None, "--database-url", help="PostgreSQL connection URL"),
    interval: float = typer.Option(2.0, "--interval", min=0.1, help="Seconds between generation attempts"),
    event_probability: float = typer.Option(0.35, "--event-probability", min=0.0, max=1.0, help="Probability of an abnormal event per tick"),
    seed: int | None = typer.Option(None, "--seed", help="Optional random seed for reproducible scenarios"),
    idle_log_every: int = typer.Option(10, "--idle-log-every", min=0, help="Log a running heartbeat after this many idle ticks; 0 disables it"),
) -> None:
    print("Starting demo production fountain.", flush=True)
    print(f"Database: {resolve_database_url(database_url)}", flush=True)
    run_fountain(database_url, interval, event_probability, seed, idle_log_every)


if __name__ == "__main__":
    typer.run(main)
