from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from psycopg import Connection, connect
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from archi_twin_context.models import DigitalTwinAlert, EnrichedAlert

DEFAULT_DATABASE_URL = "postgresql://archi:archi@localhost:5432/archi_twin_context"


def resolve_database_url(database_url: str | None = None) -> str:
    return database_url or os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL


def open_connection(database_url: str | None = None) -> Connection[dict[str, Any]]:
    return connect(resolve_database_url(database_url), row_factory=dict_row)


class PostgresAlertSource:
    """PostgreSQL polling adapter for Digital Twin alert queues"""

    def __init__(self, conn: Connection[dict[str, Any]]) -> None:
        self.conn = conn

    def claim_alerts(self, limit: int) -> list[DigitalTwinAlert]:
        return [alert_from_row(row) for row in claim_new_alert_rows(self.conn, limit)]

    def mark_enriched(self, alert_id: str) -> None:
        with self.conn.transaction():
            mark_alert_enriched(self.conn, alert_id)

    def mark_failed(self, alert_id: str, error_message: str) -> None:
        with self.conn.transaction():
            mark_alert_failed(self.conn, alert_id, error_message)


class PostgresEnrichmentResultSink:
    """PostgreSQL sink for dashboard-ready enrichment results"""

    def __init__(self, conn: Connection[dict[str, Any]]) -> None:
        self.conn = conn

    def store(self, enriched_alert: EnrichedAlert) -> None:
        with self.conn.transaction():
            store_enriched_alert(self.conn, enriched_alert)


def insert_alert(conn: Connection[dict[str, Any]], alert: DigitalTwinAlert) -> None:
    payload = alert.model_dump(mode="json")
    conn.execute(
        """
        INSERT INTO twin_alerts (
            alert_id, asset_id, alert_type, severity, value_json, unit, message, payload_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (alert_id) DO NOTHING
        """,
        (
            alert.alert_id,
            alert.asset_id,
            alert.alert_type,
            alert.severity,
            Jsonb(alert.value),
            alert.unit,
            alert.message,
            Jsonb(payload),
        ),
    )


def insert_twin_event(conn: Connection[dict[str, Any]], alert: DigitalTwinAlert) -> None:
    payload = alert.model_dump(mode="json")
    conn.execute(
        """
        INSERT INTO twin_events (
            asset_id, event_type, severity, value_json, unit, message, payload_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            alert.asset_id,
            alert.alert_type,
            alert.severity,
            Jsonb(alert.value),
            alert.unit,
            alert.message,
            Jsonb(payload),
        ),
    )


def update_asset_status(conn: Connection[dict[str, Any]], asset_id: str, status: str) -> None:
    conn.execute(
        """
        UPDATE assets
        SET current_status = %s, updated_at = now()
        WHERE asset_id = %s
        """,
        (status, asset_id),
    )


def persist_demo_alert(conn: Connection[dict[str, Any]], alert: DigitalTwinAlert, status: str) -> None:
    with conn.transaction():
        update_asset_status(conn, alert.asset_id, status)
        insert_twin_event(conn, alert)
        insert_alert(conn, alert)


def claim_new_alert_rows(conn: Connection[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    with conn.transaction():
        rows = conn.execute(
            """
            SELECT id
            FROM twin_alerts
            WHERE status = 'new'
            ORDER BY created_at
            FOR UPDATE SKIP LOCKED
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
        row_ids = [row["id"] for row in rows]
        if not row_ids:
            return []

        return conn.execute(
            """
            UPDATE twin_alerts
            SET status = 'processing', error_message = NULL
            WHERE id = ANY(%s)
            RETURNING *
            """,
            (row_ids,),
        ).fetchall()


def mark_alert_enriched(conn: Connection[dict[str, Any]], alert_id: str) -> None:
    conn.execute(
        """
        UPDATE twin_alerts
        SET status = 'enriched', processed_at = now(), error_message = NULL
        WHERE alert_id = %s
        """,
        (alert_id,),
    )


def mark_alert_failed(conn: Connection[dict[str, Any]], alert_id: str, error_message: str) -> None:
    conn.execute(
        """
        UPDATE twin_alerts
        SET status = 'failed', processed_at = now(), error_message = %s
        WHERE alert_id = %s
        """,
        (error_message, alert_id),
    )


def store_enriched_alert(conn: Connection[dict[str, Any]], enriched_alert: EnrichedAlert) -> None:
    record = enriched_alert_record(enriched_alert)
    conn.execute(
        """
        INSERT INTO enriched_alerts (
            alert_id,
            asset_id,
            alert_type,
            severity,
            risk_level,
            recommended_owner,
            recommended_bpmn_process,
            mapped_element_id,
            mapped_element_name,
            business_impact_json,
            impact_tree_json,
            trace_json,
            enriched_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (alert_id) DO UPDATE SET
            risk_level = EXCLUDED.risk_level,
            recommended_owner = EXCLUDED.recommended_owner,
            recommended_bpmn_process = EXCLUDED.recommended_bpmn_process,
            mapped_element_id = EXCLUDED.mapped_element_id,
            mapped_element_name = EXCLUDED.mapped_element_name,
            business_impact_json = EXCLUDED.business_impact_json,
            impact_tree_json = EXCLUDED.impact_tree_json,
            trace_json = EXCLUDED.trace_json,
            enriched_json = EXCLUDED.enriched_json,
            created_at = now()
        """,
        (
            record["alert_id"],
            record["asset_id"],
            record["alert_type"],
            record["severity"],
            record["risk_level"],
            record["recommended_owner"],
            record["recommended_bpmn_process"],
            record["mapped_element_id"],
            record["mapped_element_name"],
            Jsonb(record["business_impact_json"]),
            Jsonb(record["impact_tree_json"]),
            Jsonb(record["trace_json"]),
            Jsonb(record["enriched_json"]),
        ),
    )


def alert_from_row(row: Mapping[str, Any]) -> DigitalTwinAlert:
    payload = row.get("payload_json")
    if isinstance(payload, Mapping):
        return DigitalTwinAlert.model_validate(payload)

    timestamp = row.get("created_at")
    if isinstance(timestamp, datetime):
        timestamp_value = timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    else:
        timestamp_value = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return DigitalTwinAlert(
        alert_id=str(row["alert_id"]),
        asset_id=str(row["asset_id"]),
        alert_type=str(row["alert_type"]),
        severity=str(row["severity"]),
        value=row.get("value_json"),
        unit=row.get("unit"),
        timestamp=timestamp_value,
        message=row.get("message"),
    )


def enriched_alert_record(enriched_alert: EnrichedAlert) -> dict[str, Any]:
    impact_tree_json = None
    if enriched_alert.impact_tree is not None:
        impact_tree_json = enriched_alert.impact_tree.model_dump(mode="json")

    return {
        "alert_id": enriched_alert.alert.alert_id,
        "asset_id": enriched_alert.alert.asset_id,
        "alert_type": enriched_alert.alert.alert_type,
        "severity": enriched_alert.alert.severity,
        "risk_level": enriched_alert.risk_level,
        "recommended_owner": enriched_alert.recommended_owner,
        "recommended_bpmn_process": enriched_alert.recommended_bpmn_process,
        "mapped_element_id": enriched_alert.mapped_element.id,
        "mapped_element_name": enriched_alert.mapped_element.name,
        "business_impact_json": enriched_alert.business_impact,
        "impact_tree_json": impact_tree_json,
        "trace_json": enriched_alert.trace,
        "enriched_json": enriched_alert.model_dump(mode="json"),
    }
