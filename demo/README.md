# Demo Runtime

This directory contains local test infrastructure, not core product logic.

The demo stack starts PostgreSQL, a small production fountain and the enrichment engine. It is useful for exercising the adapter and enrichment flow end to end while keeping the actual `archi_twin_context` package focused on adapters, enrichment and reporting.

Run it from the repository root:

```bash
docker compose -f demo/docker-compose.yml up --build
```

The fountain writes plausible abnormal production events into the demo PostgreSQL schema. Real Digital Twin integrations should implement the adapter contracts in `src/archi_twin_context/adapters/base.py` instead of depending on the demo fountain.
