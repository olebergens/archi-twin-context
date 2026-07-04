CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    default_status TEXT NOT NULL DEFAULT 'running',
    current_status TEXT NOT NULL DEFAULT 'running',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS twin_events (
    id BIGSERIAL PRIMARY KEY,
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    value_json JSONB,
    unit TEXT,
    message TEXT,
    payload_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS twin_alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_id TEXT NOT NULL UNIQUE,
    asset_id TEXT NOT NULL REFERENCES assets(asset_id),
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    value_json JSONB,
    unit TEXT,
    message TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    payload_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ,
    error_message TEXT,
    CONSTRAINT twin_alerts_status_check CHECK (status IN ('new', 'processing', 'enriched', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_twin_alerts_status_created_at ON twin_alerts(status, created_at);
CREATE INDEX IF NOT EXISTS idx_twin_events_asset_created_at ON twin_events(asset_id, created_at DESC);

CREATE TABLE IF NOT EXISTS enriched_alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_id TEXT NOT NULL UNIQUE REFERENCES twin_alerts(alert_id),
    asset_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    recommended_owner TEXT NOT NULL,
    recommended_bpmn_process TEXT,
    mapped_element_id TEXT NOT NULL,
    mapped_element_name TEXT NOT NULL,
    business_impact_json JSONB NOT NULL,
    impact_tree_json JSONB,
    trace_json JSONB NOT NULL,
    enriched_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_enriched_alerts_asset_created_at ON enriched_alerts(asset_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_enriched_alerts_risk_level ON enriched_alerts(risk_level);

INSERT INTO assets (asset_id, name, asset_type)
VALUES
    ('cnc-01', 'CNC Milling Machine 01', 'cnc-machine'),
    ('assembly-robot-02', 'Assembly Robot 02', 'robot'),
    ('packaging-line-03', 'Packaging Line 03', 'packaging-line')
ON CONFLICT (asset_id) DO NOTHING;
